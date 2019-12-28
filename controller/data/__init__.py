from . import view, api

views = [
    view.TripitakaListHandler, view.TripitakaHandler, view.DataListHandler,
    view.DataPageHandler, view.DataPageViewHandler, view.DataPagePublishHandler,
]

handlers = [
    api.DataAddOrUpdateApi, api.DataDeleteApi, api.DataUploadApi,
    api.FetchDataTasksApi, api.SubmitDataTasksApi, api.ConfirmFetchDataTasksApi,
    api.DataGenJsApi,
]
