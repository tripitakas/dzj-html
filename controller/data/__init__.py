from . import view, api

views = [
    view.TripitakaListHandler, view.TripitakaHandler, view.DataListHandler,
    view.DataPageInfoHandler, view.DataPageListHandler,
    view.DataPageViewHandler,
]

handlers = [
    api.DataAddOrUpdateApi, api.DataDeleteApi, api.DataUploadApi, api.DataGenJsApi,
    api.DataPageUpdateSourceApi, api.DataPageExportCharApi,
]
