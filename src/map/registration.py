"""Geometric Map Registration for Georeferenced Overlay.

Computes and maintains the affine/similarity transformation between canonical
world coordinates (or interactive reference map space) and native game map pixel space.
Includes confidence metrics and strict rejection criteria for unreliable registrations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, List, Optional, Tuple, Union

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # Fallback to pure numpy when cv2 not available


@dataclass
class TransformResult:
    """Result of geometric map registration calibration."""
    matrix: np.ndarray = field(default_factory=lambda: np.eye(3, dtype=np.float64)[:2])
    scale: float = 1.0
    rotation_deg: float = 0.0
    translation: Tuple[float, float] = (0.0, 0.0)
    mean_reprojection_error: float = float("inf")
    p95_reprojection_error: float = float("inf")
    inlier_count: int = 0
    total_points: int = 0
    confidence: float = 0.0
    is_valid: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "scale": self.scale,
            "rotation_deg": self.rotation_deg,
            "translation": self.translation,
            "mean_reprojection_error": self.mean_reprojection_error,
            "p95_reprojection_error": self.p95_reprojection_error,
            "inlier_count": self.inlier_count,
            "total_points": self.total_points,
            "confidence": self.confidence,
            "is_valid": self.is_valid,
        }


class MapRegistration:
    """Estimates and stores transformation between world/reference coordinates and screen pixels."""

    def __init__(
        self,
        max_allowed_error: float = 5.0,
        min_confidence_threshold: float = 0.60,
    ) -> None:
        self.max_allowed_error = float(max_allowed_error)
        self.min_confidence_threshold = float(min_confidence_threshold)
        self._matrix: Optional[np.ndarray] = None  # 2x3 affine matrix
        self._inverse_matrix: Optional[np.ndarray] = None
        self._latest_result: TransformResult = TransformResult()

    @property
    def is_calibrated(self) -> bool:
        """True if a valid, reliable registration transformation is active."""
        return self._latest_result.is_valid and self._matrix is not None

    @property
    def confidence(self) -> float:
        """Registration confidence in [0.0, 1.0]."""
        return self._latest_result.confidence

    @property
    def matrix(self) -> Optional[np.ndarray]:
        """Current 2x3 affine projection matrix."""
        return self._matrix

    @property
    def latest_result(self) -> TransformResult:
        """Full calibration metrics from latest registration."""
        return self._latest_result

    def set_transformation_matrix(
        self,
        matrix: np.ndarray,
        confidence: float = 1.0,
        mean_error: float = 0.0,
    ) -> None:
        """Directly set a known calibrated 2x3 affine matrix."""
        mat = np.array(matrix, dtype=np.float64)
        if mat.shape == (3, 3):
            mat = mat[:2]
        if mat.shape != (2, 3):
            raise ValueError(f"Matrix must have shape (2, 3) or (3, 3), got {mat.shape}")

        self._matrix = mat
        self._update_inverse()

        # Decompose scale, rotation, translation
        a, b, tx = mat[0]
        c, d, ty = mat[1]
        scale_x = math.hypot(a, b)
        scale_y = math.hypot(c, d)
        scale = (scale_x + scale_y) / 2.0
        rotation_deg = math.degrees(math.atan2(-b, a))

        is_valid = confidence >= self.min_confidence_threshold and mean_error <= self.max_allowed_error
        self._latest_result = TransformResult(
            matrix=mat,
            scale=scale,
            rotation_deg=rotation_deg,
            translation=(float(tx), float(ty)),
            mean_reprojection_error=mean_error,
            p95_reprojection_error=mean_error,
            confidence=confidence,
            is_valid=is_valid,
        )

    def register_from_control_points(
        self,
        src_points: Union[np.ndarray, List[Tuple[float, float]]],
        dst_points: Union[np.ndarray, List[Tuple[float, float]]],
        max_error_thresh: Optional[float] = None,
    ) -> TransformResult:
        """Estimate similarity/affine transform from corresponding control points.

        Args:
            src_points: Coordinates in source/reference/world space (N, 2).
            dst_points: Corresponding coordinates in destination/native map pixel space (N, 2).
            max_error_thresh: Maximum acceptable mean reprojection error in pixels.

        Returns:
            TransformResult containing matrix, errors, and validity flag.
        """
        thresh = max_error_thresh if max_error_thresh is not None else self.max_allowed_error
        src_arr = np.array(src_points, dtype=np.float32).reshape(-1, 2)
        dst_arr = np.array(dst_points, dtype=np.float32).reshape(-1, 2)

        n_pts = len(src_arr)
        if n_pts < 2 or len(dst_arr) != n_pts:
            result = TransformResult(
                total_points=n_pts,
                is_valid=False,
                confidence=0.0,
            )
            self._latest_result = result
            self._matrix = None
            self._inverse_matrix = None
            return result

        # Compute similarity transformation (translation, isotropic scale, rotation)
        matrix = None
        inliers = np.ones(n_pts, dtype=bool)

        if cv2 is not None and n_pts >= 3:
            try:
                m_cv, inliers_mask = cv2.estimateAffinePartial2D(
                    src_arr.reshape(-1, 1, 2),
                    dst_arr.reshape(-1, 1, 2),
                    method=cv2.RANSAC,
                    ransacReprojThreshold=thresh,
                )
                if m_cv is not None:
                    matrix = m_cv
                    if inliers_mask is not None:
                        inliers = inliers_mask.ravel() == 1
            except Exception:
                matrix = None

        # Fallback to linear least squares similarity solve
        if matrix is None:
            matrix = self._solve_similarity_least_squares(src_arr, dst_arr)

        if matrix is None:
            result = TransformResult(total_points=n_pts, is_valid=False, confidence=0.0)
            self._latest_result = result
            self._matrix = None
            self._inverse_matrix = None
            return result

        # Evaluate reprojection errors
        errs = self._compute_point_errors(src_arr, dst_arr, matrix)
        inlier_errs = errs[inliers] if np.any(inliers) else errs
        mean_err = float(np.mean(inlier_errs))
        p95_err = float(np.percentile(inlier_errs, 95))
        inlier_count = int(np.sum(inliers))
        inlier_ratio = float(inlier_count / n_pts)

        # Decompose parameters
        a, b, tx = matrix[0]
        c, d, ty = matrix[1]
        scale = float(math.hypot(a, b))
        rotation_deg = float(math.degrees(math.atan2(-b, a)))

        # Quality & Rejection criteria
        error_score = max(0.0, 1.0 - (mean_err / thresh))
        confidence = float(error_score * inlier_ratio)
        is_valid = bool(
            mean_err <= thresh
            and inlier_count >= min(3, n_pts)
            and inlier_ratio >= 0.70
            and confidence >= self.min_confidence_threshold
        )

        result = TransformResult(
            matrix=matrix,
            scale=scale,
            rotation_deg=rotation_deg,
            translation=(float(tx), float(ty)),
            mean_reprojection_error=mean_err,
            p95_reprojection_error=p95_err,
            inlier_count=inlier_count,
            total_points=n_pts,
            confidence=confidence,
            is_valid=is_valid,
        )

        self._latest_result = result
        if is_valid:
            self._matrix = matrix
            self._update_inverse()
        else:
            self._matrix = None
            self._inverse_matrix = None

        return result

    def project(self, x: float, y: float) -> Tuple[float, float]:
        """Project coordinate (x, y) into native map screen pixel coordinates.

        Raises:
            ValueError: If registration is not calibrated or rejected due to low confidence.
        """
        if not self.is_calibrated or self._matrix is None:
            raise ValueError("MapRegistration is not calibrated or has insufficient confidence.")

        px = self._matrix[0, 0] * x + self._matrix[0, 1] * y + self._matrix[0, 2]
        py = self._matrix[1, 0] * x + self._matrix[1, 1] * y + self._matrix[1, 2]
        return float(px), float(py)

    def unproject(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """Convert native screen pixel coordinates back to source/world coordinates.

        Raises:
            ValueError: If registration is not calibrated.
        """
        if not self.is_calibrated or self._inverse_matrix is None:
            raise ValueError("MapRegistration is not calibrated or cannot be inverted.")

        wx = self._inverse_matrix[0, 0] * screen_x + self._inverse_matrix[0, 1] * screen_y + self._inverse_matrix[0, 2]
        wy = self._inverse_matrix[1, 0] * screen_x + self._inverse_matrix[1, 1] * screen_y + self._inverse_matrix[1, 2]
        return float(wx), float(wy)

    def compute_reprojection_error(
        self,
        src_points: Union[np.ndarray, List[Tuple[float, float]]],
        dst_points: Union[np.ndarray, List[Tuple[float, float]]],
        matrix: Optional[np.ndarray] = None,
    ) -> float:
        """Compute mean Euclidean reprojection error in pixels."""
        mat = matrix if matrix is not None else self._matrix
        if mat is None:
            return float("inf")
        src_arr = np.array(src_points, dtype=np.float32).reshape(-1, 2)
        dst_arr = np.array(dst_points, dtype=np.float32).reshape(-1, 2)
        errs = self._compute_point_errors(src_arr, dst_arr, mat)
        return float(np.mean(errs)) if len(errs) > 0 else float("inf")

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def _update_inverse(self) -> None:
        """Compute and cache inverse 2x3 affine matrix."""
        if self._matrix is None:
            self._inverse_matrix = None
            return
        m33 = np.eye(3, dtype=np.float64)
        m33[:2] = self._matrix
        try:
            inv33 = np.linalg.inv(m33)
            self._inverse_matrix = inv33[:2]
        except np.linalg.LinAlgError:
            self._inverse_matrix = None

    @staticmethod
    def _compute_point_errors(
        src_pts: np.ndarray,
        dst_pts: np.ndarray,
        matrix: np.ndarray,
    ) -> np.ndarray:
        """Compute pairwise Euclidean errors between projected src and dst."""
        ones = np.ones((len(src_pts), 1), dtype=np.float32)
        src_homo = np.hstack([src_pts, ones])
        proj = np.matmul(src_homo, matrix.T)
        return np.linalg.norm(proj - dst_pts, axis=1)

    @staticmethod
    def _solve_similarity_least_squares(
        src_pts: np.ndarray,
        dst_pts: np.ndarray,
    ) -> Optional[np.ndarray]:
        """Fit similarity transform (a, b, tx, ty) with pure numpy linear solve."""
        n = len(src_pts)
        if n < 2:
            return None

        # Build design matrix: for each point (x, y):
        # [ x, -y, 1, 0 ] [ a  ]   [ u ]
        # [ y,  x, 0, 1 ] [ b  ] = [ v ]
        #                 [ tx ]
        #                 [ ty ]
        A = np.zeros((2 * n, 4), dtype=np.float64)
        b_vec = np.zeros((2 * n,), dtype=np.float64)

        for i in range(n):
            x, y = src_pts[i]
            u, v = dst_pts[i]
            A[2 * i] = [x, -y, 1.0, 0.0]
            A[2 * i + 1] = [y, x, 0.0, 1.0]
            b_vec[2 * i] = u
            b_vec[2 * i + 1] = v

        try:
            params, residuals, rank, s = np.linalg.lstsq(A, b_vec, rcond=None)
            a, b_val, tx, ty = params
            return np.array([
                [a, -b_val, tx],
                [b_val, a, ty],
            ], dtype=np.float64)
        except Exception:
            return None
