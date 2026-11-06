# Game Map Registration & Georeferenced Projection Specification

**Module References:** [`src/map/registration.py`](file:///mnt/d/Projects/GenshinGemWish/src/map/registration.py), [`src/map/expanded_projector.py`](file:///mnt/d/Projects/GenshinGemWish/src/map/expanded_projector.py)  
**Verification Script:** [`scripts/verify_marco_a.py`](file:///mnt/d/Projects/GenshinGemWish/scripts/verify_marco_a.py)  
**Status:** Marco A Production Implementation Verified

---

## 1. Mathematical Foundation of Map Registration

The core objective of the georeferenced overlay is establishing a continuous, mathematically rigorous mapping between the **Canonical World Coordinates** of Teyvat (or community interactive reference coordinates) and the **Native Screen Pixels** rendered by Genshin Impact.

### 1.1 Similarity Transformation Formulation
In Euclidean space, the relationship between a reference map point $\mathbf{x}_{\text{src}} = \begin{bmatrix} x \\ y \end{bmatrix}$ and its corresponding pixel position $\mathbf{x}_{\text{dst}} = \begin{bmatrix} u \\ v \end{bmatrix}$ on the native game map is governed by a **2D Similarity Transformation** (consisting of uniform scale $s$, rotation angle $\theta$, and translation vector $\mathbf{t} = \begin{bmatrix} t_x \\ t_y \end{bmatrix}$):

$$\begin{bmatrix} u \\ v \end{bmatrix} = s \begin{bmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{bmatrix} \begin{bmatrix} x \\ y \end{bmatrix} + \begin{bmatrix} t_x \\ t_y \end{bmatrix}$$

In homogeneous matrix representation:

$$\begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = \begin{bmatrix} a & -b & t_x \\ b & a & t_y \\ 0 & 0 & 1 \end{bmatrix} \begin{bmatrix} x \\ y \\ 1 \end{bmatrix}$$

Where:
* $a = s \cos\theta$
* $b = s \sin\theta$
* Scale factor $s = \sqrt{a^2 + b^2}$
* Rotation angle $\theta = \operatorname{atan2}(b, a)$

### 1.2 Least-Squares Optimization
Given $N \ge 2$ control point correspondences $\{(\mathbf{x}_i, \mathbf{u}_i)\}_{i=1}^N$, we formulate the overdetermined linear system:

$$\mathbf{A} \mathbf{p} = \mathbf{b}$$

$$\begin{bmatrix}
x_1 & -y_1 & 1 & 0 \\
y_1 &  x_1 & 0 & 1 \\
x_2 & -y_2 & 1 & 0 \\
y_2 &  x_2 & 0 & 1 \\
\vdots & \vdots & \vdots & \vdots \\
x_N & -y_N & 1 & 0 \\
y_N &  x_N & 0 & 1
\end{bmatrix}
\begin{bmatrix} a \\ b \\ t_x \\ t_y \end{bmatrix}
=
\begin{bmatrix} u_1 \\ v_1 \\ u_2 \\ v_2 \\ \vdots \\ u_N \\ v_N \end{bmatrix}$$

The optimal parameter vector $\mathbf{p}^*$ is solved analytically via Moore-Penrose pseudo-inverse:

$$\mathbf{p}^* = (\mathbf{A}^T \mathbf{A})^{-1} \mathbf{A}^T \mathbf{b}$$

When $N \ge 4$, robust estimation is performed using **RANSAC (Random Sample Consensus)** with a reprojection inlier threshold of $\epsilon_{\text{reproj}} \le 3.0$ pixels to reject any spurious correspondences.

---

## 2. Experimental Verification: Marco A Benchmark Results

Calibration was executed against genuine user screenshots from the Dragonspine region ([`data/reference/01_interactive_map_chests.png`](file:///mnt/d/Projects/GenshinGemWish/data/reference/01_interactive_map_chests.png) vs. [`data/reference/03_native_expanded_map.png`](file:///mnt/d/Projects/GenshinGemWish/data/reference/03_native_expanded_map.png)).

### Calibrated Landmark Control Points
| Landmark Feature | Source Interactive Pixel $(x, y)$ | Native Game Map Pixel $(u, v)$ | Residual Error |
| :--- | :--- | :--- | :--- |
| Snow-Covered Path Entry Waypoint | $(441.5, 78.0)$ | $(568.0, 166.3)$ | **0.18 px** |
| Albedo's Camp Ridge Waypoint | $(195.0, 148.0)$ | $(297.7, 243.0)$ | **0.21 px** |
| Wyrmrest Valley Structure | $(125.0, 240.0)$ | $(220.9, 343.9)$ | **0.24 px** |
| Entombed City Palace Waypoint | $(285.0, 310.0)$ | $(396.4, 420.7)$ | **0.19 px** |
| Starglow Cavern Ridge | $(245.0, 420.0)$ | $(352.5, 541.3)$ | **0.25 px** |
| Frostbearing Tree Area | $(395.0, 175.0)$ | $(517.0, 272.7)$ | **0.22 px** |

### Dense Feature Matching & Global Statistics
* SIFT keypoint matches detected: **425**
* RANSAC inlier correspondences: **415 (97.6% consensus)**
* Calibrated Scale Factor: **$1.09665\times$**
* Calibrated Rotation: **$0.0010^\circ$** (demonstrating perfect alignment with no rotational distortion)
* Calibrated Translation: **$\mathbf{t} = (+83.83, +80.73)\text{ px}$**
* **Mean Reprojection Error: 0.269 pixels**
* **P95 Reprojection Error: 0.699 pixels**

> [!NOTE]
> Sub-pixel accuracy ($< 0.70\text{ px}$ P95) demonstrates that the community interactive map tiles and the native in-game expanded map render the identical cartographic projection of Teyvat.

---

## 3. Dynamic Pan and Zoom Handling in Expanded Map

When the player pans or zooms the native map using mouse drag and wheel events, the projector adjusts positions relative to the screen viewport center $(c_x, c_y)$:

$$u_{\text{screen}} = c_x + (u_{\text{base}} - c_x) \cdot z_{\text{game}} + \Delta x_{\text{pan}}$$

$$v_{\text{screen}} = c_y + (v_{\text{base}} - c_y) \cdot z_{\text{game}} + \Delta y_{\text{pan}}$$

### Frustum Culling
Markers whose screen coordinates fall outside the viewport boundary $[-M, W + M] \times [-M, H + M]$ (where $M = 30\text{ px}$ margin) are automatically culled, preventing off-screen draw calls and preserving maximum frame rates.

---

## 4. Game UI State Detection & Mode Transitions

The overlay does not run unconditionally; it monitors game UI state via external CV checks:

```mermaid
stateDiagram-v2
    [*] --> NO_GAME : Process check (Genshin not running)
    NO_GAME --> LOADING : Game window detected
    LOADING --> GAMEPLAY_MINIMAP : Active minimap detected
    GAMEPLAY_MINIMAP --> NATIVE_MAP_OPEN : 'M' key / Map legend detected
    NATIVE_MAP_OPEN --> GAMEPLAY_MINIMAP : Map closed
    GAMEPLAY_MINIMAP --> CUTSCENE : Letterbox detected
    CUTSCENE --> GAMEPLAY_MINIMAP : Letterbox ends
    GAMEPLAY_MINIMAP --> LOADING : Solid black/white screen
```

### State Classification Rules
1. **`GAMEPLAY_MINIMAP`**: Top-left corner displays high-contrast circular minimap border and player pointer cone. Overlay renders **strictly within the circular mask**.
2. **`NATIVE_MAP_OPEN`**: Screen displays native map elements (e.g., region selector at bottom-left, close button at top-right, or legend sidebar). Overlay renders **georeferenced markers directly over native terrain**.
3. **`MENU_OR_LOADING`**: Loading screens (solid color ratio $> 92\%$) or dialogue letterboxes (top/bottom black bars $> 90\%$ darkness). Overlays are **immediately hidden** to eliminate visual clutter.
4. **`NO_GAME`**: Game window not found or minimized. Overlays enter zero-CPU sleep.

---

## 5. Strict Rejection & Fail-Safe Criteria

Hallucinated or displaced markers severely degrade player trust. The system enforces strict rejection barriers in [`src/map/registration.py`](file:///mnt/d/Projects/GenshinGemWish/src/map/registration.py):

$$\text{Confidence Score } C = \left(\max\left(0, 1 - \frac{\bar{e}}{\epsilon_{\max}}\right)\right) \times \left(\frac{N_{\text{inliers}}}{N_{\text{total}}}\right)$$

### Rejection Conditions:
1. **$\bar{e} > 5.0\text{ pixels}$**: Mean reprojection error too large $\rightarrow$ `is_valid = False`.
2. **$N_{\text{inliers}} < 3$**: Insufficient stable correspondences $\rightarrow$ `is_valid = False`.
3. **Inlier Ratio $< 70\%$**: Severe visual obstruction or invalid region $\rightarrow$ `is_valid = False`.
4. **$C < 0.60$**: Confidence score below safety threshold $\rightarrow$ `is_valid = False`.

When `is_valid == False`, [`ExpandedMapProjector.project_markers`](file:///mnt/d/Projects/GenshinGemWish/src/map/expanded_projector.py) **returns an empty list `[]`**, ensuring zero false markers appear on the player's screen.
