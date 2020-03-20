from . import view, api, tripitaka

views = [
    tripitaka.TripitakaListHandler, tripitaka.TripitakaViewHandler,
    view.DataListHandler, view.PageListHandler, view.PageInfoHandler, view.CharListHandler,
    view.CharStatisticHandler,
]

handlers = [
    api.DataUpsertApi, api.DataUploadApi, api.DataDeleteApi, api.PageExportCharsApi,
    api.DataGenJsApi, api.UpdatePageSourceApi, api.UpdateCharBatchApi,
]
