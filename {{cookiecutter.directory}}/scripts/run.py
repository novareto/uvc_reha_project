# Start up script

def start(config):
    import bjoern
    import uvcreha
    import uvcreha.mq
    import uvcreha.tasker
    import reha.client
    import importscan
    from rutter.urlmap import URLMap
    from reiter.application.startup import make_logger
    from uvcreha.startup import Applications

    logger = make_logger("uvcreha")
    apps = Applications.from_configuration(config, logger=logger)

    app = URLMap()
    app['/'] = apps.browser
    app['/api'] = apps.api
    app['/backend'] = apps.backend

    importscan.scan(uvcreha)
    importscan.scan(reha.client)

    #tasker = uvcreha.tasker.Tasker.create(apps)
    #tasker.start()

    try:
        if not config.server.socket:
            logger.info(
                "Server started on "
                f"http://{config.server.host}:{config.server.port}")
            #pprint.pprint(list(apps.browser.routes))
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
        #tasker.stop()
        pass


if __name__ == "__main__":
    import pathlib
    from zope.dottedname import resolve
    from omegaconf import OmegaConf
    from reiter.application.startup import environment, make_logger

    def resolve_path(path: str) -> str:
        path = pathlib.Path(path)
        return str(path.resolve())

    OmegaConf.register_resolver("path", resolve_path)
    OmegaConf.register_resolver("class", resolve.resolve)
    baseconf = OmegaConf.load('config.yaml')
    override = OmegaConf.from_cli()
    config = OmegaConf.merge(baseconf, override)
    with environment(**config.environ):
        start(config)
