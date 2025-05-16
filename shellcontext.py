from dgp_intra import create_app
from dgp_intra.extensions import db
from dgp_intra.models import User

app = create_app()

# For Flask shell context
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
    }