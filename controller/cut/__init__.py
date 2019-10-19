from . import api, view

views = [
    view.CutHandler, view.CutEditHandler
]
handlers = [
    api.CutApi, api.CutEditApi, api.GenerateCharIdApi
]
