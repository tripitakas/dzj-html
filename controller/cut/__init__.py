from . import api, view

views = [
    view.CutHandler, view.CutEditHandler
]
handlers = [
    api.CutTaskApi, api.CutEditApi, api.GenerateCharIdApi
]
