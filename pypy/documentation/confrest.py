from py.__.documentation.confrest import *

class PyPyPage(Page): 
    def fill(self):
        super(PyPyPage, self).fill()
        self.menubar[:] = html.div(
            html.a("news", href="news.html", class_="menu"), " ",
            html.a("doc", href="index.html", class_="menu"), " ",
            html.a("contact", href="contact.html", class_="menu"), " ", 
            html.a("getting-started", href="getting_started.html", class_="menu"), " ",
            html.a("issue", 
                   href="https://codespeak.net/issue/pypy-dev/", 
                   class_="menu"), 
            " ", id="menubar")
    

class Project(Project): 
    title = "PyPy" 
    stylesheet = 'style.css'
    encoding = 'latin1' 
    prefix_title = "PyPy"
    logo = html.div(
        html.a(
            html.img(alt="PyPy", height="110", id="pyimg", 
                     src="/pypy/img/py-web1.png", width="149")))
    Page = PyPyPage 


