import pytest
from nva.selenium.server import ServerThread
from axe_selenium_python import Axe


@pytest.mark.usefixtures("browser_driver")
@pytest.mark.usefixtures("embedded_apps")
class TestBrowser:

    @pytest.fixture(scope="function")
    def server(self):
        server = ServerThread(self.wsgi)
        server.start()
        yield server
        server.stop()

    def test_sel(self, server):
        self.driver.get(server.host)
        axe = Axe(self.driver)
        axe.inject()
        results = axe.run()
        axe.write_results(results, 'a11y.json')
