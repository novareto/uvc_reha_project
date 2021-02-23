import pathlib
from omegaconf import OmegaConf
from reiter.application.startup import environment, make_logger


def start(config):
    import importscan
    import uvcreha
    import uvcreha.mq
    from uvcreha.startup import Applications
    from rutter.urlmap import URLMap

    importscan.scan(uvcreha)

    logger = make_logger("uvcreha")
    apps = Applications.from_configuration(config, logger=logger)

    app = URLMap()
    app["/"] = apps.browser

    # Serving the app
    AMQPworker = uvcreha.mq.Worker(app, config.amqp)
    AMQPworker()


def resolve_path(path: str) -> str:
    path = pathlib.Path(path)
    return str(path.resolve())


if __name__ == "__main__":
    OmegaConf.register_resolver("path", resolve_path)
    baseconf = OmegaConf.load("config.yaml")
    override = OmegaConf.from_cli()
    config = OmegaConf.merge(baseconf, override)
    with environment(**config.environ):
        start(config)
