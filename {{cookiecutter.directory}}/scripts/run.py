import colorlog
import contextlib
import functools
import json
import logging
import os
import pathlib
from minicli import cli, run
from omegaconf import OmegaConf


@contextlib.contextmanager
def environment(**environ):
    """Temporarily set the process environment variables.
    """
    old_environ = dict(os.environ)
    os.environ.update(dict(environ))
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


def make_logger(name, level=logging.DEBUG) -> logging.Logger:
    logger = colorlog.getLogger(name)
    logger.setLevel(level)
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(red)s%(levelname)-8s%(reset)s '
        '%(yellow)s[%(name)s]%(reset)s %(green)s%(message)s'))
    logger.addHandler(handler)
    return logger


def configure(config: OmegaConf):
    from uvcreha.configure import setup
    #from reha.client.app import backend
    from repoze.vhm.middleware import VHMExplicitFilter

    app = setup(config)
    #backend.configure(config)
    #app['/backend'] = backend

    # Global middlewares
    if config.vhm:
        app = VHMExplicitFilter(app, **config.vhm)

    return app


@cli
def http(configfile: pathlib.Path):
    import bjoern
    import importscan
    from fs.osfs import OSFS
    from uvcreha import jsonschema
    from uvcreha import contenttypes

    from pkg_resources import iter_entry_points

    config = OmegaConf.load(configfile)
    logger = make_logger("uvcreha")

    # First thing, we load the jsonschemas
    if config.app.storage.schemas:
        with OSFS(config.app.storage.schemas) as fs:
            for schema in fs.listdir('/'):
                if schema.endswith('.json'):
                    with fs.open(schema) as fd:
                        data = json.load(fd)
                        jsonschema.store.add(
                            data.get('id', schema), data)

    with environment(**config.environ):
        app = configure(config)

        # Loading plugins
        for plugin in iter_entry_points('reiter.application.modules'):
            module = plugin.load()
            importscan.scan(module)
            logger.info(f"Plugin '{plugin.name}' loaded.")

        logger.info(str(list(jsonschema.store.schemas.keys())))
        logger.info(str(dict(contenttypes.registry.items())))

        try:
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
        except KeyboardInterrupt:
            pass
        finally:
            pass


if __name__ == "__main__":
    from zope.dottedname import resolve

    def resolve_path(path: str) -> str:
        path = pathlib.Path(path)
        return str(path.resolve())

    OmegaConf.register_resolver("path", resolve_path)
    OmegaConf.register_resolver("class", resolve.resolve)
    run()
