from . import view
from . import api_algorithm as g

views = [
    view.DataTripitakaHandler, view.DataVolumeHandler, view.DataSutraHandler, view.DataReelHandler,
    view.DataPageHandler, view.DataSearchCbetaHandler, view.DataPunctuationHandler
]
handlers = [
    g.GenerateCharIdApi,
]
