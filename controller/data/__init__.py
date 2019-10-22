from . import view, api

views = [
    view.DataPageHandler, view.TripitakaListHandler, view.TripitakaHandler,
    view.DataTripitakaHandler, view.DataVolumeHandler, view.DataSutraHandler, view.DataReelHandler,
    view.ImportImagesHandler,
]

handlers = [
    api.DataAddOrUpdateApi, api.DataDeleteApi, api.DataUploadApi
]
