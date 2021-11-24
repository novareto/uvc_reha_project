import fanstatic
import logging
import pathlib
import importscan
import uvcreha
import uvcreha.app
import uvcreha.api
import uvcreha.auth.source
import uvcreha.user
import uvcreha.browser
import uvcreha.contents
import uvcreha.emailer
import uvcreha.plugins
import uvcreha.request
import reiter.auth.meta
import reiter.auth.filters
import reiter.auth.components
import reiter.auth.utilities
from reha.prototypes import contents
from reha.prototypes.workflows.user import user_workflow


### Logging

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = logging.FileHandler('var/event.log')
fh.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(fh)


### Setup Contents

uvcreha.contents.registry.register('user', contents.User)
uvcreha.contents.registry.register('file', contents.File)
uvcreha.contents.registry.register('document', contents.Document)
uvcreha.contents.registry.register('preferences', contents.Preferences)
# Load essentials
importscan.scan(uvcreha.browser)
importscan.scan(uvcreha.api)


### Database

#from database.arango import init_database
import reha.sql
from database.sql import init_database

database = init_database(reha.sql.mappers)


### Middlewares

# Session
session_environ = "uvcreha.session"

session = uvcreha.plugins.session_middleware(
    pathlib.Path("var/sessions"), secret='secret',
    cookie_name="uvcreha.cookie", 
    salt="abc123" 
)

session_getter = reiter.auth.components.session_from_environ(
    session_environ
)


### Utilities

# flash
flash = uvcreha.plugins.flash_messages(
  session_key=session_environ
)


# Email
emailer = uvcreha.emailer.SecureMailer(
    user=None,
    password=None,
    emitter="uvcreha@novareto.de"
)

# 2FA
twoFA = reiter.auth.utilities.TwoFA(
    session_key=session_environ
)


# Auth
authentication = reiter.auth.components.Auth(
    sources=[],
    user_key="uvcreha.principal",
    session_getter=session_getter,
    filters=(
        reiter.auth.filters.security_bypass([
            "/login"
        ]),
        reiter.auth.filters.secured(path="/login"),
        reiter.auth.filters.filter_user_state(states=(
            user_workflow.states.inactive,
            user_workflow.states.closed
        )),
        reiter.auth.filters.TwoFA("/2FA", twoFA.check_twoFA)
    )
)

# Theme
import reha.siguv_theme
ui = reha.siguv_theme.get_theme(
    request_type=uvcreha.app.Request,
    resources=[
        uvcreha.browser.resources.f_input_group,
        uvcreha.browser.resources.webpush_subscription
    ]
)
importscan.scan(reha.siguv_theme)

### Application

browser_app = uvcreha.app.Application(
    secret=b"verygeheim",
    database=database,
    ui=ui,
    routes=uvcreha.browser.routes,
    authentication=authentication,
    actions=uvcreha.browser.actions,
    utilities={
#        "webpush": webpush,
        "emailer": emailer,
        "flash": flash,
        "twoFA": twoFA,
    }
)

browser_app.authentication.sources.append(
    uvcreha.auth.source.DatabaseSource(browser_app)
)


### OpenAPI Application 


api_app = uvcreha.app.API(
    secret=b"verygeheim",
    database=database,
    routes=uvcreha.api.routes,
    utilities={
#        "webpush": webpush,
        "emailer": emailer,
        "database": database,
    }
)


### Backend

import reha.client
import reha.client.app
import reiter.auth.testing

admin_authentication = reiter.auth.components.Auth(
    user_key="backend.principal",
    session_getter=session_getter,
    sources=[reiter.auth.testing.DictSource({"admin": "admin"})],
    filters=(
        reiter.auth.filters.security_bypass([
            "/login"
        ]),
        reiter.auth.filters.secured(path="/login"),
        #reiter.auth.filters.filter_user_state(states=(
        #    user_workflow.states.inactive,
        #    user_workflow.states.closed
        #)),
    )
)


class AdminRequest(reha.client.app.AdminRequest, uvcreha.app.Request):
    pass


backend_app = uvcreha.app.Application(
    secret=b"verygeheim",
    database=database,
    authentication=admin_authentication,
    actions=reha.client.app.actions,
    ui=ui,
    routes=reha.client.app.routes,
    request_factory=AdminRequest,
    utilities={
        "webpush": webpush,
        "emailer": emailer,
        "flash": flash,
    }
)


reha.client.install_me(backend_app)  # backend

# Load content types
from uvcreha.contents import load_content_types
load_content_types(pathlib.Path("./schemas/content_types"))




### Plugins

# OZG
#import uv.ozg
#uv.ozg.install_me(browser_app)
#uv.ozg.app.load_content_types(pathlib.Path("./schemas/ozg_content_types"))


# Own Package
#import reha.example
#importscan.scan(reha.example)


### SERVER

# URL Mapping
from horseman.mapping import Mapping
wsgi_app = Mapping({
    "/": fanstatic.Fanstatic(
        session(browser_app, environ_key=session_environ, secure=False),
        compile=False,
        recompute_hashes=True,
        bottom=True,
        publisher_signature="static"
    ),
    "/backend": fanstatic.Fanstatic(
        session(backend_app, environ_key=session_environ, secure=False),
        compile=True,
        recompute_hashes=True,
        bottom=True,
        publisher_signature="static"
    ),
    "/api": api_app
})
