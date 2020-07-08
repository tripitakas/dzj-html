from . import view, api, api_task as at, view_task as vt, api_ocr as ao

views = [
    view.PageListHandler, view.PageBrowseHandler, view.PageViewHandler, view.PageInfoHandler,
    view.PageBoxHandler, view.PageOrderHandler, view.PageTxtHandler,
    view.PageTxtMatchHandler, view.PageFindCmpHandler,
    vt.PageTaskCutHandler, vt.PageTaskTextHandler,
    vt.PageTaskListHandler, vt.PageTaskStatHandler, vt.PageTaskResumeHandler,
]

handlers = [
    api.PageDeleteApi, api.PageUpsertApi, api.PageSourceApi,
    api.PageCmpTxtApi, api.PageFindCmpTxtApi, api.PageCmpTxtNeighborApi,
    api.PageBoxApi, api.PageOrderApi, api.PageCharBoxApi, api.PageCharTxtApi,
    api.PageTxtMatchApi, api.PageTxtMatchDiffApi, api.PageStartGenCharsApi, api.PageStartCheckMatchApi,
    at.PageTaskPublishApi, at.PageTaskCutApi, at.PageTaskTextApi,
    ao.FetchTasksApi, ao.SubmitTasksApi, ao.ConfirmFetchApi,
]
