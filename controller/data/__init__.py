from . import data as t
from . import api_algorithm as g

views = [
    t.DataTripitakaHandler, t.DataEnvelopHandler, t.DataVolumeHandler, t.DataSutraHandler, t.DataReelHandler,
    t.DataPageHandler, t.DataSearchCbetaHandler
]
handlers = [
    g.GenerateCharIdApi,
]
