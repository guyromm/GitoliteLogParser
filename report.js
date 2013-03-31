      // Load the Visualization API and the piechart package.
      google.load('visualization', '1.0', {'packages':['corechart']});

      // Set a callback to run when the Google Visualization API is loaded.
      google.setOnLoadCallback(drawChart);

      // Callback that creates and populates a data table,
      // instantiates the pie chart, passes in the data and
      // draws it.
      function drawChart() {

        // Create the data table.
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Topping');
        data.addColumn('number', 'Times');
        data.addRows(times);

        // Set chart options
        var options = {'title':'Amount of access',
                       'width':1200,
                       'height':800};

        // Instantiate and draw our chart, passing in some options.
        var chart = new google.visualization.BarChart(document.getElementById('chart_div'));
        chart.draw(data, options);
	for (var u in overtime)
	  {
	      var d = overtime[u];
	      var rd=[];
	      for (var date in d)
	      {
		  var app = [date,d[date]];
		  rd.push(app);
		  console.log(app); 
	      }
	      rd.sort(function(s1,s2) {
		  if (s1[0]>s2[0]) return 1;
		  else if (s1[0]<s2[0]) return -1;
		  else return 0;
	      })
	      var dv = $('<div></div>').attr('id',u);
	      dv.append($('<h3></h3>').text(u));
	      var chel = $('<div></div>').addClass('chart')
	      dv.append(chel);

	      var data = google.visualization.arrayToDataTable(rd,true);
	      var ch = new google.visualization.ColumnChart(chel[0]);
	      var options = {
		  title: u+' over time',
		  hAxis: {title: 'Dates', titleTextStyle: {color: 'red'}},
		  width:1200,
		  heig:800
              };

	      ch.draw(data,options);
	      //console.log(dv.html());
	      $('body').append(dv);

	  }
      }
