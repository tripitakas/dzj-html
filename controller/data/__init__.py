from . import view, api

views = [
    view.DataPageHandler, view.TripitakaListHandler, view.TripitakaHandler,
    view.DataTripitakaHandler, view.DataVolumeHandler, view.DataSutraHandler, view.DataReelHandler,
    view.ImportImagesHandler,
]

handlers = [
    api.DataAddOrUpdateApi, api.DataDeleteApi, api.DataUploadApi, api.GetReadyPagesApi,
    api.PublishPageTaskApi, api.PublishImportImagesApi, api.PickPageTasksApi, api.PickImportImagesApi,
    api.SubmitOcrApi, api.SubmitUploadCloudApi, api.SubmitImportImagesApi, api.DeleteImportImagesApi,
]
