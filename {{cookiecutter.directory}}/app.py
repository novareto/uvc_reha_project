import fanstatic
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


import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# setup contents
uvcreha.contents.registry.register('user', contents.User)
uvcreha.contents.registry.register('file', contents.File)
uvcreha.contents.registry.register('document', contents.Document)
uvcreha.contents.registry.register('preferences', contents.Preferences)


#from database.arango import init_database
from database.sql import init_database


import reha.sql

database = init_database(reha.sql.mappers)


# Load essentials
importscan.scan(uvcreha.browser)
importscan.scan(uvcreha.api)


### Middlewares

# Session
session_environ = "uvcreha.session"

session = uvcreha.plugins.session_middleware(
    pathlib.Path("var/sessions"), secret='secret',
    cookie_name="uvcreha.cookie"
)

session_getter = reiter.auth.components.session_from_environ(
    session_environ
)


### Utilities

# flash
flash = uvcreha.plugins.flash_messages(
  session_key=session_environ
)


# webpush
webpush = uvcreha.plugins.webpush_plugin(
    public_key=pathlib.Path("config/identities/public_key.pem"),
    private_key=pathlib.Path("config/identities/private_key.pem"),
    vapid_claims={
        "sub": "mailto:cklinger@novareto.de",
        "aud": "https://updates.push.services.mozilla.com"
    }
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

import reha.siguv_theme
ui = reha.siguv_theme.get_theme(request_type=uvcreha.app.Request)


browser_app = uvcreha.app.Application(
    secret=b"verygeheim",
    database=database,
    ui=ui,
    routes=uvcreha.browser.routes,
    authentication=authentication,
    utilities={
        "webpush": webpush,
        "emailer": emailer,
        "flash": flash,
        "twoFA": twoFA,
    }
)

browser_app.authentication.sources.append(
    uvcreha.auth.source.DatabaseSource(browser_app)
)


api_app = uvcreha.app.API(
    secret=b"verygeheim",
    database=database,
    routes=uvcreha.api.routes,
    utilities={
        "webpush": webpush,
        "emailer": emailer,
        "database": database,
    }
)

# Backend
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
    ui=ui,
    routes=reha.client.app.routes,
    request_factory=AdminRequest,
    utilities={
        "webpush": webpush,
        "emailer": emailer,
        "flash": flash,
    }
)


importscan.scan(reha.client)  # backend

# import themes
import reha.siguv_theme
#import reha.ukh_theme

#importscan.scan(reha.ukh_theme)  # Collecting UI elements
importscan.scan(reha.siguv_theme)  # Collecting UI elements


# Plugins
#import uv.ozg
#import uv.ozg.app

#importscan.scan(uv.ozg)
#uv.ozg.app.load_content_types(pathlib.Path("./content_types"))

#import reha.example
#importscan.scan(reha.example)

#from reha.example.principal import MyPrincipal
#uvcreha.contents.registry.register('user', MyPrincipal)


# Load content types
from uvcreha.contents import load_content_types

load_content_types(pathlib.Path("./schemas/content_types"))


# URL Mapping
from horseman.mapping import Mapping
wsgi_app = Mapping({
    "/": fanstatic.Fanstatic(
        session(browser_app, environ_key=session_environ, secure=False),
        compile=True,
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


# Run me
#bjoern.run(
#    host="0.0.0.0",
#    port=8082,
#    reuse_port=True,
#    wsgi_app=wsgi_app
#)
