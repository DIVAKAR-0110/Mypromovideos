
document.addEventListener('DOMContentLoaded', () => {
  if (typeof REPORT_DATA === 'undefined' || !REPORT_DATA) return;

  const companies = Object.keys(REPORT_DATA);
  const COLORS = ['#6c63ff','#00d4aa','#ffc107','#ff4d6d','#17a2b8'];

  const chartDefaults = {
    responsive: true,
    plugins: {
      legend: { labels: { color: '#b0b8c8', font: { family: 'Inter', size: 12 } } },
    },
    scales: {
      x: { ticks: { color: '#8892a4' }, grid: { color: 'rgba(255,255,255,.05)' } },
      y: { ticks: { color: '#8892a4' }, grid: { color: 'rgba(255,255,255,.05)' } },
    },
  };

  const subCtx = document.getElementById('subChart');
  if (subCtx) {
    new Chart(subCtx, {
      type: 'bar',
      data: {
        labels: companies,
        datasets: [{
          label: 'Subscribers',
          data: companies.map(c => REPORT_DATA[c]?.channel?.subscribers || 0),
          backgroundColor: companies.map((_, i) => COLORS[i % COLORS.length]),
          borderRadius: 8,
        }],
      },
      options: {
        ...chartDefaults,
        plugins: { ...chartDefaults.plugins, legend: { display: false } },
      },
    });
  }

  const engCtx = document.getElementById('engChart');
  if (engCtx) {
    new Chart(engCtx, {
      type: 'bar',
      data: {
        labels: companies,
        datasets: [{
          label: 'Engagement Rate (%)',
          data: companies.map(c => REPORT_DATA[c]?.analytics?.avg_engagement_rate || 0),
          backgroundColor: companies.map((_, i) => COLORS[i % COLORS.length]),
          borderRadius: 8,
        }],
      },
      options: {
        ...chartDefaults,
        plugins: { ...chartDefaults.plugins, legend: { display: false } },
      },
    });
  }
});
