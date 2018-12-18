//重置密码
function resetPsw(id, name) {
  swal({
        title: '确定重置 ' + name + ' 的密码吗？',
        text: '密码重置后无法恢复！',
        type: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#DD6B55',
        confirmButtonText: '确定重置',
        cancelButtonText: '取消',
        closeOnConfirm: false
      },
      function () {
        postApi('/pwd/reset/' + id, {}, function (data) {
          swal({
            title: '重置成功',
            html: true,
            text: name + ' 的密码已重置为 <b id="pwd">' + data.password + '</b>',
            type: 'success'
          });
        }, function (msg) {
          showError('重置失败', msg);
        });
      });
}
//删除帐号
function delUser(id, name, email) {
  swal({
        title: '确定删除 ' + name + ' 的帐号吗？',
        text: '帐号删除后无法恢复！',
        type: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#DD6B55',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        closeOnConfirm: false
      },
      function () {
        postApi('/user/logout', {data: {id: id, name: name, email: email}}, function () {
          showSuccess('删除成功', name + ' 的帐号已经被删除。');
          refresh();
        }, function (msg) {
          showError('删除失败', msg);
        });
      });
}
//修改角色
function modifyRole(id, name, account, auth) {
  var $list = $('.authority-list');
  var $name = $('#modal-name');
  var $groups = $('#groups');
  var user = users.filter(function (p) {
    return p.id === id;
  })[0];
  var groups = getGroups(user.school);
  var groupIndex = -1;

  $('#roleModal').modal();
  $('#modal-account').html(account);
  $name.val(name);
  $('#self').toggle(id === currentUserId);

  $list.find('label').each(function (i, el) {
    var label = el.innerHTML;
    var input = $list.find('#' + el.getAttribute('for'));
    input.prop('checked', auth.indexOf(label) >= 0);
  });

  $('.groups-form').toggle(groups.length && user.groups.length < 2);
  $('#groups [value]').remove();
  groups.forEach(function (g, i) {
    $groups.append('<option value="' + g[0] + '">' + g[1] + '</option>');
    if (user.groups.length === 1 && g[0] === user.groups[0][0]) {
      groupIndex = i;
    }
  });
  $groups[0].options.selectedIndex = groupIndex + 1;

  $('#roleModal .btn-primary').unbind('click').click(function (event) {
    event.stopPropagation();
    event.preventDefault();

    var info = {id: id, email: account, name: $name.val()};
    var authority = [];
    $list.find('label').each(function (i, el) {
      var label = el.innerHTML;
      var input = $list.find('#' + el.getAttribute('for'));
      if (input.is(':checked')) {
        authority.push(label);
      }
    });
    info.authority = authority.join(',');

    if ($groups.val()) {
      info.team = $groups.val();
      user.groups = [$groups.val(), $groups[0].options[$groups[0].options.selectedIndex].label];
    }

    function success(code) {
      showSuccess('修改成功', code === 1009 ? '用户信息没有发生改变。' : name + ' 的信息已修改。');
      $('#roleModal [data-dismiss="modal"]').unbind('click').click();
      refresh();
    }

    postApi('/user/change', {data: info}, success, function (msg, code) {
      if (code === 1009) {
        return success(code);
      }
      showError('修改失败', msg);
    });
  });
}

function getGroups(school) {
    var groups = [];
    users.forEach(function (p) {
      if (p.school === school && p.groups.length) {
        p.groups.forEach(function (g) {
          if (g[0] && groups.filter(function (t) {
                return t[0] === g[0];
              }).length === 0) {
            groups.push(g);
          }
        });
      }
    });
    groups.sort(function (a, b) {
      return a[1].localeCompare(b[1]);
    });
    return groups;
  }

function refresh() {
  var table = $('#datatable').DataTable();
  var page = table.page();
  table.ajax.reload(function () {
    table.page(page).draw(false);
  });
}

jQuery.extend(jQuery.fn.dataTableExt.oSort, {
  'time-pre': function (a) {
    return serverYear && !/^20\d\d-/.test(a) ? serverYear + a : a;
  },
  'time-asc': function (a, b) {
    return a < b ? -1 : (a > b ? 1 : 0);
  },
  'time-desc': function (a, b) {
    return a < b ? 1 : (a > b ? -1 : 0);
  }
});

var serverYear = null;
var users = [];

$(document).ready(function () {
  $('#datatable').dataTable({
    searching: true,
    ordering: true,
    autoWidth: true,
    columns: [
      {data: 'order'},
      {data: 'name'},
      {data: 'email', visible: false},
      {data: 'group'},
      {data: 'short_authority'},
      {data: 'short_create_time', sType: 'time'},
      {data: 'short_last_time', sType: 'time'},
      {data: 'op', orderable: false}
    ],
    oLanguage: {
      sUrl: datatable_language_file
    },
    ajax: {
      url: '/api/user/list',
      processing: true,
      dataSrc: function (data) {
        if (data.error) {
          $('.content .row').hide();
          $('.content').text(data.error);
          return [];
        }
        var manager = (data.authority || '').indexOf('管理员') >= 0;
        var teacher = (data.authority || '').indexOf('教师') >= 0;
        var school_mgr = (data.authority || '').indexOf('校管员') >= 0;
        var table = $('#datatable').DataTable();

        $('.panel-title > span:first-child').text(manager ? '全部用户' : data.school_name + (school_mgr ? '' : ' ' + data.team) +
            (teacher ? ' 用户管理' : ' 组内人员'));
        table.column(2).visible(false);   // email
        if (data.not_auth) {
          table.column(6).visible(false);
          table.column(5).visible(false);
        }
        serverYear = data.time && data.time.substring(0, 5);
        users = data.items || [];
        if (data.visit_code) {
          $('.visit_code').html(data.school_name + '的邀请码为 <b>' + data.visit_code + '</b>，可邀请本校师生以此码注册加入。');
          $('.panel-title .visit_code').html('邀请码: <b>' + data.visit_code + '</b>');
        }
        var a = '<a href="javascript:void(0)" onclick="';
        var items = users.map(function (p, i) {
          p.order = 1 + i;
          p.short_create_time = (p.create_time || '').substring(2, 10);
          p.short_last_time = (p.last_time || p.create_time).substring(2, 10);
          p.short_authority = p.authority;
          p.group = p.groups.length ? ('<a href="/g/_">'.replace('_', p.groups[0][0]) + p.groups[0][1].substring(0, 8)
            + '</a>' + (p.groups.length > 1 ? '(' + p.groups.length + ')' : '')) : '';
          if (manager) {
            p.group = '<a href="/s/' + p.school + '">' + p.school_name.substring(0, 6) + '</a> ' + p.group;
          }

          if (data.not_auth) {
            p.op = '无权限';
            p.email = '';
          } else {
            p.op = '';
            if ((manager || school_mgr) && p.id !== currentUserId) {
              p.op += a + "resetPsw('%_id', '%_name');\">密码</a>";
            }
            p.op += a + "modifyRole('%_id', '%_name', '%_mail', '%_auth');\">修改</a>";
            if ((manager || school_mgr) && p.id !== currentUserId) {
              p.op += a + "delUser('%_id', '%_name', '%_mail');\">删除</a>";
            }
            p.op = p.op.replace(/%_id/g, p.id).replace(/%_name/g, p.name)
                .replace(/%_mail/g, p.email).replace(/%_auth/g, p.authority);
          }
          p.name = '<a href="javascript:void(0);" onclick="window.location.href=\'/u/'
                + p.id + '\'">' + p.name + (p.id === currentUserId ? ' <small>(自己)</small>' : '') + '</a>';
          return p;
        });

        $('.active_clients').html('当前有 ' + data.active_clients + ' 个活动用户：' + data.active_users);

        return items;
      },
      xhrFields: {
        withCredentials: true
      },
      error: function (data, e) {
        $('.content .row').hide();
        $('.content').text((data.responseJSON || {}).error || '网络访问失败，请稍后重试。');
      }
    }
  });
});
