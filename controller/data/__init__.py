from . import view, api, tripitaka

views = [
    tripitaka.TripitakaListHandler, tripitaka.TripitakaViewHandler,
    view.DataListHandler, view.PageListHandler, view.PageInfoHandler, view.CharListHandler,
]

handlers = [
    api.DataUpsertApi, api.DataUploadApi, api.DataDeleteApi, api.UpdateSourceApi,
    api.PageExportCharsApi, api.DataGenJsApi,
]
