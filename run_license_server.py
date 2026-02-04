"""
Script auxiliar para correr un servidor HTTP simple para mockear licencias.
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys

port = 8081
print(f"Servidor de licencias corriendo en http://localhost:{port}/licencias_mock.json")
httpd = HTTPServer(('localhost', port), SimpleHTTPRequestHandler)
httpd.serve_forever()
