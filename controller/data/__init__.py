from . import view, api

views = [
    view.DataPageHandler, view.TripitakaListHandler, view.TripitakaHandler,
    view.DataTripitakaHandler, view.DataVolumeHandler, view.DataSutraHandler, view.DataReelHandler,
]

handlers = [
    api.DataAddOrUpdateApi, api.DataDeleteApi, api.DataUploadApi,
    api.FetchDataTasksApi, api.SubmitDataTasksApi, api.ConfirmFetchDataTasksApi,
]
