# run_dev.py
from dgp_intra import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
