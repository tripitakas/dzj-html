from . import api, view

views = [
    view.RecognitionHandler, view.RecognitionViewHandler
]
handlers = [
    api.RecognitionApi, api.SubmitRecognitionApi,
]
