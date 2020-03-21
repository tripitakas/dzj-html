from . import api, view

views = [
    view.LobbyTaskHandler, view.MyTaskHandler, view.PageTaskAdminHandler, view.ImageTaskAdminHandler,
    view.PageTaskResumeHandler, view.PageTaskStatisticHandler,
    view.TaskDetailHandler, view.TaskSampleHandler,
]

handlers = [
    api.PublishImageTasksApi, api.RepublishTaskApi,
    api.GetReadyPagesApi, api.AssignTasksApi, api.DeleteTasksApi, api.UpdateTaskApi,
    api.PickTaskApi, api.ReturnTaskApi, api.FinishTaskApi, api.LockTaskApi,
    api.UnlockTaskApi, api.InitTestTasksApi,
]
