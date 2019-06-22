from . import api_common, api_admin, api_text, view_admin, view_do, view_lobby, view_my, view_text

views = [
    view_lobby.TaskLobbyHandler, view_my.MyTaskHandler, view_admin.TaskAdminHandler,
    view_admin.TaskCutStatusHandler, view_admin.TaskTextStatusHandler,
    view_do.CutProofDetailHandler, view_do.CutReviewDetailHandler, view_do.CharOrderProofHandler,
    view_text.TextProofHandler, view_text.TextReviewHandler,

]
handlers = [
    api_common.GetPageApi, api_common.GetReadyPagesApi, api_common.UnlockTasksApi,
    api_common.PickCutProofTaskApi, api_common.PickCutReviewTaskApi,
    api_common.PickTextProofTaskApi, api_common.PickTextReviewTaskApi,
    api_common.SaveCutProofApi, api_common.SaveCutReviewApi,
    api_text.SaveTextProofApi, api_text.SaveTextReviewApi,
    api_admin.PublishTasksApi, api_admin.PublishTasksFileApi,
]
modules = {'TextArea': view_text.TextArea}
