import pathlib
from omegaconf import OmegaConf
from reiter.application.startup import environment, make_logger


def start(config):
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

    app = URLMap()
    app["/"] = apps.browser

    # Serving the app
    AMQPworker = docmanager.mq.Worker(app, config.amqp)
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
