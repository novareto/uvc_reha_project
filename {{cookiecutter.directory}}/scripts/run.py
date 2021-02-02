import functools
import pathlib
from fanstatic import Fanstatic
from omegaconf import OmegaConf
from reiter.application.startup import environment, make_logger
from horseman.prototyping import WSGICallable


def fanstatic_middleware(config) -> WSGICallable:
    return functools.partial(Fanstatic, **config)


def session_middleware(config) -> WSGICallable:
    import cromlech.session
    import cromlech.sessions.file

    handler = cromlech.sessions.file.FileStore(
        config.session.cache, 3000
    )
    manager = cromlech.session.SignedCookieManager(
        config.session.cookie_secret,
        handler,
        cookie=config.session.cookie_name
    )
    return cromlech.session.WSGISessionManager(
        manager, environ_key=config.env.session)


def start(config):
    import bjoern
    import importscan
    import docmanager
    import docmanager.mq
    from docmanager.startup import Applications
    from rutter.urlmap import URLMap
    from ukh.reha.app import UKHRequest

    importscan.scan(docmanager)

    logger = make_logger("docmanager")
    apps = Applications.from_configuration(config, logger=logger)
    apps.browser.request_factory = UKHRequest

    apps.browser.register_middleware(
        fanstatic_middleware(config.app.assets), order=0)  # very first.

    apps.browser.register_middleware(
        session_middleware(config.app), order=1)

    app = URLMap()
    app['/'] = apps.browser
    app['/api'] = apps.api

    # Serving the app

    if not config.server.socket:
        logger.info(
            "Server started on "
            f"http://{config.server.host}:{config.server.port}")
        bjoern.run(
            app, config.server.host,
            int(config.server.port), reuse_port=True)
    else:
        logger.info(
            f"Server started on socket {config.server.socket}.")

        bjoern.run(app, config.server.socket)


def resolve_path(path: str) -> str:
    path = pathlib.Path(path)
    return str(path.resolve())


if __name__ == "__main__":
    OmegaConf.register_resolver("path", resolve_path)
    baseconf = OmegaConf.load('config.yaml')
    override = OmegaConf.from_cli()
    config = OmegaConf.merge(baseconf, override)
    with environment(**config.environ):
        start(config)
