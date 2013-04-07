      // Load the Visualization API and the piechart package.
      google.load('visualization', '1.0', {'packages':['corechart']});

      // Set a callback to run when the Google Visualization API is loaded.
      google.setOnLoadCallback(drawChart);

      // Callback that creates and populates a data table,
      // instantiates the pie chart, passes in the data and
      // draws it.
      function drawChart() {

        // Create the data table.
        var users_data = new google.visualization.DataTable();
        users_data.addColumn('string', 'Topping');
        users_data.addColumn('number', 'Times');
        users_data.addRows(times);

	  var repos_data = new google.visualization.DataTable();
	  repos_data.addColumn('string','Repository');
	  repos_data.addColumn('number','Times');
	  repos_data.addRows(repos);

        // Set chart options
        var options = {'title':'Amount of access',
                       'width':1200,
                       'height':800};

        // Instantiate and draw our chart, passing in some options.
        var chart = new google.visualization.BarChart(document.getElementById('chart_div'));
        chart.draw(users_data, options);

	var repochart = new google.visualization.PieChart(document.getElementById('repos_div'));
	repochart.draw(repos_data,options);

	  for (var u in repoovertime)
	  {
	      var d = repoovertime[u];
	      var dv = $('<div></div>').attr('id',u);
	      dv.append($('<h3></h3>').text(u));
	      var chel = $('<div></div>').addClass('chart')
	      dv.append(chel);

	      var data = new google.visualization.DataTable();
	      data.addColumn('string','Date');
	      for (var k in repos) data.addColumn('number',repos[k][0]);
	      var out=[]
	      for (var date in d)
	      {
		  out.push([date,d[date]]);
	      }

	      out.sort(function(e1,e2) {
		  if (e1[0]>e2[0]) return 1;
		  else if (e1[0]<e2[0]) return -1;
		  else return 0;
	      });
	      for (var i in out)
	      {
		  var date = out[i][0];
		  
		  var spl = date.split('-');
		  var dt = new Date(spl[0],spl[1],spl[2]);

		  var row=[];
		  row.push(date);
		  for (var repo in repos) {
		      var r = repos[repo][0];
		      row.push(out[i][1][r]);
		  }

		  data.addRow(row);
	      }


	      var ch = new google.visualization.SteppedAreaChart(chel[0]);
	      var options = {
		  title: u+' over time',
		  hAxis: {title: 'Dates', titleTextStyle: {color: 'red'}},
		  isStacked:true,
		  width:1200,
		  heig:800
              };

	      ch.draw(data,options);
	      //console.log(dv.html());
	      $('body').append(dv);
	      delete data;

	  }
      }
