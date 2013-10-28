
var CoursesClass = Class({
    __init__: function(self) {
        self.stuff = 'things';
    },
    set_flag: function (self, cid, flag) {
        var node = $('li.course_' + cid);
        var badge = $('.course-badge', node);
        var now = badge[0].className.split(' ')[2];
        if (now == 'completed' || now == 'registered') {
            if (!confirm('This course has been marked '+now+'. Do you really want to change it?')){
                return;
            }
        }
        // badge.css('background-color', 'pink');
        badge.attr('class', 'badge course-badge loading');
        jQuery.ajax(URLS['ajax-set-flag'], {
            data: {'cid':cid, 'flag':flag},
            error: function (xhr, tstatus, error) {
                alert('error sending data to server: '+tstatus);
            },
            success: function (data, tstatus, xhr) {
                badge.attr('class', 'badge course-badge '+flag);
            }
        });
    }
});

var Courses = CoursesClass();

function do_collapse(e, what, collapse, all) {
    e.preventDefault();
    e.stopPropagation();
    var mychildren = $(what.parentNode.getAttribute('data-target'));
    if (!collapse && !mychildren.hasClass('in')){
        mychildren.collapse('show');
    }
    var children = mychildren.find(all ? ' ul' : ' > li > ul');
    children.collapse(collapse?'hide':'show');
    return false;
}

$('.expandsome').click(function(e){
    return do_collapse(e, this, false, false);
});
$('.expandall').click(function(e){
    return do_collapse(e, this, false, true);
});
$('.collapsesome').click(function(e){
    return do_collapse(e, this, true, false);
});
$('.collapseall').click(function(e){
    return do_collapse(e, this, true, true);
});

$('#hide-notdone').click(function(e){
    $('li.course.notdone')[$(this).hasClass('active')?'show':'hide']();
    $('li.hidenotdone')[$(this).hasClass('active')?'addClass':'removeClass']('showing');
});

$('li.hidenotdone').click(function(e){
    var node = $(this);
    node.parent().find('li.course.notdone')[node.hasClass('showing')?'hide':'show']();
    node.toggleClass('showing');
});

$('.course-badge').click(function(e){
    var node = $(this);
    var p = node.offset();
    $('#badge-dropdown').css({'top':p.top+node.height(), 'left':p.left-6})
        .attr('data-course', node.parent().attr('data-cid'));
    $('#badge-dd-parent').addClass('open');
    e.stopPropagation();
    return false;
});

$('#badge-dropdown li a').click(function(e){
    Courses.set_flag($('#badge-dropdown').attr('data-course'), this.className);
});

function ajax(url, data, success){
    jQuery.ajax(url, {
        data: data,
        dataType: 'json',
        success: function (data) {
            if (data['error']){
                alert('Server error: '+data['error']);
            } else {
                success(data);
            }
        }
    });
}

$('span.star').click(function(e){
    var node = $(this);
    if (node.hasClass('on')){
        dest = URLS['ajax-unstar'];
    } else {
        dest = URLS['ajax-star'];
    }
    var cid = node.parent().attr('data-cid');
    ajax(dest, {'cid': cid},
        function (data) {
            $('li.course_'+cid+' span.star').toggleClass('on').toggleClass('off');
        });
});

$('div.loadingbar div.course').each(function() {
    var node = $(this);
    node.qtip({
        content: node.data('id') + ' ' + node.data('name'),
        position: {
            corner: {
                tooltip: 'bottomMiddle',
                target: 'topMiddle'
            }
        },
        show: {
            delay: 0,
            effect: {
                type: 'fade',
                length: 0
            }
        },
        style: {
            border: {
                width: 2,
                radius: 10
            },
            tip: true,
            name: 'cream'
        }
    });
});



