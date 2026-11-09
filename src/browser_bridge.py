"""Small standalone native-messaging executable; never imports the overlay UI."""
from src.live.browser_connector import main
if __name__ == '__main__':
    raise SystemExit(main())
