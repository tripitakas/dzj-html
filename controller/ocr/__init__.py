from . import api, view

views = [
    view.RecognitionHandler, view.RecognitionViewHandler, view.ImportImagesHandler
]
handlers = [
    api.RecognitionApi, api.SubmitRecognitionApi,
    api.RecognitionApi, api.SubmitRecognitionApi, api.ImportImagesApi, api.ImportMetaApi, api.FetchResultApi,
]
