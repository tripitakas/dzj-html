from . import view, api, ocr, ext

views = [
    view.PageListHandler, view.PageBrowseHandler, view.PageViewHandler, view.PageInfoHandler,
    view.PageBoxHandler, view.PageOrderHandler, view.PageTaskCutHandler,
    view.PageTxtMatchHandler, view.PageTaskTxtMatchHandler,
    view.PageFindCmpHandler,
    view.PageTaskListHandler, view.PageTaskStatHandler, view.PageTaskResumeHandler,
    ext.PageTxtTaskHandler, ext.PageTxtHandler, ext.PageTextHandler,
]

handlers = [
    ocr.FetchTasksApi, ocr.SubmitTasksApi, ocr.ConfirmFetchApi,
    api.PageDeleteApi, api.PageUpsertApi, api.PageGenCharsApi, api.PageSourceApi,
    api.PageBoxApi, api.CharBoxApi, api.PageOrderApi, api.PageTaskCutApi,
    api.PageCmpTxtApi, api.PageCmpTxtNeighborApi,
    api.PageTxtMatchApi, api.PageTxtMatchDiffApi, api.PageTaskTxtMatchApi,
    api.PageTaskPublishApi, api.PageCheckMatchApi, api.PageFindCmpApi,
    ext.PageTxtDiffApi, ext.PageDetectCharsApi,
]
