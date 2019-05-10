from . import api, view_admin, view_do, view_lobby, view_my

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
    api.GetPageApi, api.GetPagesApi, api.UnlockTasksApi,
    api.PickCutProofTaskApi, api.PickCutReviewTaskApi, api.PickTextProofTaskApi, api.PickTextReviewTaskApi,
    api.SaveCutProofApi, api.SaveCutReviewApi,
    api.PublishTasksApi,
]
