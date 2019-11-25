from . import api, view

views = [
    view.SearchCbetaHandler, view.PunctuationHandler
]

handlers = [
    api.CbetaSearchApi, api.PunctuationApi,
]
