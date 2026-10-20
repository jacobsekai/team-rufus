"""AWS Lambda entry point.

API Gateway invokes ``handler``; apig-wsgi translates the API Gateway event
into a normal WSGI request so the same Flask app runs locally and on Lambda.
"""

import logging

from apig_wsgi import make_lambda_handler

from . import create_app


app = create_app()
# Flask logs warnings and above by default; INFO adds the chat usage lines
# (token counts and stop reasons only, never message text).
app.logger.setLevel(logging.INFO)
handler = make_lambda_handler(app)
