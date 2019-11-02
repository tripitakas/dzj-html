from . import api, view

views = [
    view.SearchCbetaHandler, view.PunctuationHandler, view.OcrHandler, view.OcrViewHandler,
]

handlers = [
    api.CbetaSearchApi, api.PunctuationApi,
]
