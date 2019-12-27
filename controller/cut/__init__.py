from . import api, view

views = [
    view.CutHandler, view.CutEditHandler, view.CutSampleHandler,
]
handlers = [
    api.CutTaskApi, api.CutEditApi, api.GenerateCharIdApi
]
