
TERMS = ['Winter', 'Spring', 'Summer', 'Fall'];

var Term = Class({
    __init__: function(self, shortname) {
        self.shortname = shortname;
        var parts = shortname.split('-');
        self.year = parseInt(parts[0]);
        self.termno = parseInt(parts[1]);
        self.term = TERMS[self.termno];
    },
    pretty: function(self) {
        console.log(self.termno, self.shortname);
        return self.term + ' ' + self.year;
    },
    cmp: function(terma, termb) {
        if (terma.year == termb.year){
            return terma.termno > termb.termno;
        }
        return terma.year > termb.year;
    }
});

function newterm(shortname){
    var node = $('<td class="term ' + shortname + '"><ul class="term ' + shortname + '"></ul></td>');
    var head = $('<th class="' + shortname + '">' + Term(shortname).pretty() + '<span class="delete">&times;</span></th>');
    var terms = $('td.term');
    var done = false;
    for (var i=0;i<terms.length;i++){
        var oshort = terms[i].className.split(' ')[1];
        if (oshort > shortname) {
            terms[i].parentNode.insertBefore(node[0], terms[i]);
            var th = $('th.'+oshort)[0];
            th.parentNode.insertBefore(head[0], th);
            // $('#planned-courses thead tr')[0].insertBefore(head[0], $('th.'+oshort)[0]);
            done = true;
            break;
        }
    }
    if (!done) {
        var parent = $('tr.terms')[0];
        parent.insertBefore(node[0], $('td.addterm')[0]);
        var last = $('th.addterm')[0];
        phead = $('#planned-courses thead tr')[0];
        phead.insertBefore(head[0], last);
    }
    resort();
    $('.delete', head).click(remove_term);
}

function remove_term(){
    var shortname = this.parentNode.className.split()[0];
    var longname = this.parentNode.firstChild.nodeValue;
    if ($('td.'+shortname+' li').length && !confirm('You currently are planning to take courses during this term. Really delete?')){
        return;
    }
    jQuery.ajax(URLS['remove_term'], {
        'data':{'short': shortname},
        'dataType': 'json',
        'success': function (data){
            if (data['error']){
                alert('server error: '+data['error']);
            } else  {
                $('th.'+shortname+', td.'+shortname).remove();
                var addnode = $('<li><div class="' + shortname + '">' + longname + '</div></li>');
                var current = $('ul.addterm div');
                var good = false;
                for (var i=0;i<current.length;i++){
                    if (current[i].className > shortname){
                        current[i].parentNode.parentNode.insertBefore(addnode[0], current[i].parentNode);
                        good = true;
                        break;
                    }
                }
                if (!good) {
                    addnode.appendTo($('ul.addterm'));
                }
                
                $('div', addnode).click(addterm);
            }
        }
    });
}

$('th .delete').click(remove_term);

function resort(){
    $('#planned-courses ul.term, #unorganized-courses ul').sortable(sortconfig);
}

function shownode(node, inner){
    var res = node.nodeName + '::' + node.className;
    if (inner){
        res += '  ' + node.innerHTML;
    }
    return res;
}

var sortconfig = {
    connectWith:'ul',
    cancel: 'li.completed',
    start: function (e, ui) {
        ui.helper.css({'width':250});
    },
    receive: function (e, ui, what) {
        var cid = ui.item[0].className.split(' ')[1];
        var tid = this.className.split(' ')[1];
        jQuery.ajax(URLS['move_course'], {
            'data': {'cid': cid,
                'tid': tid,
            },
            'dataType': 'json',
            success: function(data){
                if (data['error']){
                    alert('server error: '+data['error']);
                } else {
                }
            },
        });
    },
    cursorAt: {'left': 5},
    placeholder: 'placeholder',
};

$('#planned-courses ul.term, #unorganized-courses ul').sortable(sortconfig);
$('ul, li.course').disableSelection();

$('ul.addterm li div').click(addterm);

function addterm(){
    var shortname = this.className;
    $(this).addClass('loading');
    jQuery.ajax(URLS.add_term, {
        'data':{'short': shortname},
        'dataType': 'json',
        'success': function(data){
            $(this).removeClass('loading');
            if (data['error']){
                alert('server error: '+data['error']);
            } else {
                newterm(shortname);
            }
        }
    });
    $(this).parent().remove();
}


