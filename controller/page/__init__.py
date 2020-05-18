from . import view, api, ocr, ext

views = [
    view.PageListHandler, view.PageBrowseHandler, view.PageViewHandler, view.PageInfoHandler,
    view.PageBoxHandler, view.PageOrderHandler, view.PageFindCmpHandler,
    view.PageTaskListHandler, view.PageTaskStatHandler, view.PageTaskResumeHandler,
    view.PageCutTaskHandler, ext.PageTxtTaskHandler, view.PageTxtMatchHandler,
    ext.PageTxtHandler, ext.PageTextHandler,
]

handlers = [
    ocr.FetchTasksApi, ocr.SubmitTasksApi, ocr.ConfirmFetchApi,
    api.PageDeleteApi, api.PageUpsertApi,
    api.PageBoxApi, api.CharBoxApi, api.PageOrderApi, api.PageCmpTxtApi, api.PageCmpTxtNeighborApi,
    api.PageGenCharsApi, api.PageSourceApi,
    api.PageTaskPublishApi, api.PageCutTaskApi, api.PageTxtMatchApi, api.PageTxtMatchApi,
    ext.PageTxtDiffApi, ext.PageDetectCharsApi,
]
