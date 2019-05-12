from . import api_common, api_admin, view_admin, view_do, view_lobby, view_my

views = [
    view_lobby.LobbyBlockCutProofHandler, view_lobby.LobbyColumnCutProofHandler, view_lobby.LobbyCharCutProofHandler,
    view_lobby.LobbyBlockCutReviewHandler, view_lobby.LobbyColumnCutReviewHandler, view_lobby.LobbyCharCutReviewHandler,
    view_lobby.TextProofTaskLobbyHandler, view_lobby.TextReviewTaskLobbyHandler, view_lobby.TextHardTaskLobbyHandler,
    view_admin.TaskAdminHandler, view_admin.TaskCutStatusHandler, view_admin.TaskTextStatusHandler,
    view_do.CutProofDetailHandler, view_do.CutReviewDetailHandler,
    view_do.CharProofDetailHandler, view_do.CharReviewDetailHandler,
    view_my.MyTaskHandler,
]
handlers = [
    api_common.GetPageApi, api_common.GetPagesApi, api_common.UnlockTasksApi,
    api_common.PickCutProofTaskApi, api_common.PickCutReviewTaskApi,
    api_common.PickTextProofTaskApi, api_common.PickTextReviewTaskApi,
    api_common.SaveCutProofApi, api_common.SaveCutReviewApi,
    api_admin.PublishTasksApi,
]
