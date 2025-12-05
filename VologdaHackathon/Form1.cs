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
            string filePath = @"./Files/1.py";
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
            string filePath = @"./Files/2.py";
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

        private void button3_Click(object sender, EventArgs e)
        {
            string filePath = @"./Files/3.py";
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

        private void button4_Click(object sender, EventArgs e)
        {
            string filePath = @"./Files/4.py";
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
