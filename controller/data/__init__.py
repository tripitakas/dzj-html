from . import view
from . import api_algorithm as g

views = [
    view.DataTripitakaHandler, view.DataEnvelopHandler, view.DataVolumeHandler, view.DataSutraHandler, view.DataReelHandler,
    view.DataPageHandler, view.DataSearchCbetaHandler
]
handlers = [
    g.GenerateCharIdApi,
]
