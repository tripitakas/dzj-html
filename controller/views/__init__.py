#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 在 controller.views 包实现页面响应类，生成前端页面，modules 为重用网页片段的渲染类

from . import modules, home, user, task, tripitaka as t

handlers = [home.HomeHandler,
            user.UserLoginHandler, user.UserRegisterHandler,
            user.UsersAdminHandler, user.UserRolesHandler, user.UserStatisticHandler, user.UserProfileHandler,
            task.LobbyBlockCutProofHandler, task.LobbyColumnCutProofHandler, task.LobbyCharCutProofHandler,
            task.LobbyBlockCutReviewHandler, task.LobbyColumnCutReviewHandler, task.LobbyCharCutReviewHandler,
            task.CharProofDetailHandler, task.CutProofDetailHandler, task.CutReviewDetailHandler,
            task.CharReviewDetailHandler,
            task.TaskCutStatusHandler, task.TaskTextStatusHandler,
            task.TextProofTaskLobbyHandler, task.TextReviewTaskLobbyHandler, task.TextHardTaskLobbyHandler,
            task.TaskAdminHandler, task.MyTaskHandler,
            t.RsTripitakaHandler, t.TripitakaListHandler, t.TripitakaHandler, t.DataTripitakaHandler,
            t.DataEnvelopHandler, t.DataVolumeHandler, t.DataSutraHandler, t.DataReelHandler, t.DataPageHandler,
            ]

modules = {'CommonLeft': modules.CommonLeft, 'CommonHead': modules.CommonHead,
           'Pager': modules.Pager}
