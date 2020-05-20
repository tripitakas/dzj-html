from . import view, api, ocr, ext

views = [
    view.PageListHandler, view.PageBrowseHandler, view.PageViewHandler, view.PageInfoHandler,
    view.PageBoxHandler, view.PageOrderHandler, view.PageTaskCutHandler,
    view.PageTxtMatchHandler, view.PageTaskTxtMatchHandler, view.PageFindCmpHandler,
    view.PageTaskListHandler, view.PageTaskStatHandler, view.PageTaskResumeHandler,
    ext.PageTaskTxtHandler, ext.PageTxtHandler, ext.PageTextHandler,
]

handlers = [
    api.PageDeleteApi, api.PageUpsertApi, api.PageSourceApi,
    api.PageBoxApi, api.CharBoxApi, api.PageOrderApi, api.PageTaskCutApi,
    api.PageCmpTxtApi, api.PageCmpTxtNeighborApi,
    api.PageTxtMatchApi, api.PageTxtMatchDiffApi, api.PageTaskTxtMatchApi,
    api.PageTaskPublishApi, api.PageStartGenCharsApi, api.PageStartCheckMatchApi, api.PageStartFindCmpApi,
    ocr.FetchTasksApi, ocr.SubmitTasksApi, ocr.ConfirmFetchApi,
    ext.PageTxtDiffApi, ext.PageDetectCharsApi,
]
