from tornado import web

def single_file_handler(path):
    with open(path) as f:
        data = f.read()

    class _Handler(web.RequestHandler):
        def get(self):
            self.set_header("Content-Type", "text/html")
            self.finish(data)

    return _Handler
