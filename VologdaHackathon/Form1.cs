using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace VologdaHackathon
{
    public partial class Form1 : Form
    {
        public Form1()
        {
            InitializeComponent();
        }

        private void button1_Click(object sender, EventArgs e)
        {
            string filePath = Path.Combine(Application.StartupPath, "Files", "1.py");
            if (!File.Exists(filePath))
            {
                MessageBox.Show("Файл не найден!");
                return;
            }
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = filePath,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Не удалось открыть файл: {ex.Message}");
            }
        }

        private void button2_Click(object sender, EventArgs e)
        {
            string filePath = Path.Combine(Application.StartupPath, "Files", "2.py");
            if (!File.Exists(filePath))
            {
                MessageBox.Show("Файл не найден!");
                return;
            }
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = filePath,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Не удалось открыть файл: {ex.Message}");
            }
        }

        private async void button3_Click(object sender, EventArgs e)
        {
            string filePath = Path.Combine(Application.StartupPath, "Files", "3.py");
            if (!File.Exists(filePath))
            {
                MessageBox.Show("Файл не найден!");
                return;
            }
            try
            {
                ProcessStartInfo processInfo = new ProcessStartInfo
                {
                    FileName = filePath,
                    UseShellExecute = true
                };
                Process process = new Process();
                process.StartInfo = processInfo;
                process.Start();
                await process.StandardInput.WriteLineAsync(comboBox1.Text);
                process.StandardInput.Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Не удалось открыть файл: {ex.Message}");
            }
        }

        private void button4_Click(object sender, EventArgs e)
        {
            string filePath = Path.Combine(Application.StartupPath, "Files", "4.py");
            if (!File.Exists(filePath))
            {
                MessageBox.Show("Файл не найден!");
                return;
            }
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = filePath,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Не удалось открыть файл: {ex.Message}");
            }
        }
    }
}
