from . import data_view, data_api, ocr_view
from . import api_algorithm as g
from . import ocr_api

views = [
    data_view.DataTripitakaHandler, data_view.DataVolumeHandler, data_view.DataSutraHandler, data_view.DataReelHandler,
    data_view.DataPageHandler, data_view.DataSearchCbetaHandler, data_view.DataPunctuationHandler,
    # view_ocr.RecognitionHandler
]
handlers = [
    g.GenerateCharIdApi, data_api.PunctuationApi, data_api.CbetaSearchApi,
    ocr_api.RecognitionApi
]
