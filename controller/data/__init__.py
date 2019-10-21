from . import data_view, data_api, ocr_view
from . import api_algorithm as g
from . import ocr_api as api

views = [
    data_view.DataTripitakaHandler, data_view.DataVolumeHandler, data_view.DataSutraHandler, data_view.DataReelHandler,
    data_view.DataPageHandler, data_view.DataSearchCbetaHandler, data_view.DataPunctuationHandler,
    ocr_view.RecognitionHandler, ocr_view.RecognitionViewHandler, ocr_view.ImportImagesHandler,
]
handlers = [
    g.GenerateCharIdApi, data_api.PunctuationApi, data_api.CbetaSearchApi,
    api.RecognitionApi, api.SubmitRecognitionApi, api.ImportImagesApi, api.ImportMetaApi, api.FetchResultApi,
]
