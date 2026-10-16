"""AWS Lambda entry point.

API Gateway invokes ``handler``; apig-wsgi translates the API Gateway event
into a normal WSGI request so the same Flask app runs locally and on Lambda.
"""

from apig_wsgi import make_lambda_handler

from . import create_app


app = create_app()
handler = make_lambda_handler(app)
