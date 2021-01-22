from . import view, api, tripitaka as tri

views = [
    tri.TripitakaListHandler, tri.TripitakaPageHandler, tri.TripitakaDataHandler,
    view.DataListHandler, view.VariantListHandler, view.DataImportImageHandler,
]

handlers = [
    api.VariantDeleteApi, api.VariantMergeApi, api.VariantSourceApi, api.VariantCode2NorTxtApi,
    api.DataUpsertApi, api.DataUploadApi, api.DataDeleteApi,
    api.DataGenJsApi, api.PublishImportImageApi,
]
