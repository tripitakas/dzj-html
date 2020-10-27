from . import api, view

views = [
    view.TaskLobbyHandler, view.TaskMyHandler, view.TaskInfoHandler, view.TaskSampleHandler,
]

handlers = [
    api.PickTaskApi, api.ReturnTaskApi, api.UpdateTaskApi, api.RepublishTaskApi,
    api.DeleteTasksApi, api.AssignTasksApi, api.FinishTaskApi,
    api.UpdateMyTaskApi, api.InitTasksForOPTestApi,
]
