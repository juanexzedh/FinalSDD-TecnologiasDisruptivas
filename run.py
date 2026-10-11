import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "src"))
load_dotenv()

from taskcontrol import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
