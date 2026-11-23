using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;

internal static class ActinverTerminal
{
    private const string LocalUrl = "http://127.0.0.1:8765/";
    private const string HealthUrl = "http://127.0.0.1:8765/api/estado";

    [STAThread]
    private static void Main()
    {
        string repo = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".."));
        string script = Path.Combine(repo, "scripts", "iniciar-remoto.ps1");
        if (!File.Exists(script))
        {
            MessageBox.Show("No encuentro el iniciador junto a este ejecutable. Mantenga el archivo .exe en la carpeta launcher del proyecto.",
                "Actinver Terminal", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        if (!IsHealthy())
        {
            try
            {
                var start = new ProcessStartInfo("powershell.exe");
                start.Arguments = "-NoProfile -ExecutionPolicy Bypass -File \"" + script + "\"";
                start.WorkingDirectory = repo;
                start.UseShellExecute = true;
                start.WindowStyle = ProcessWindowStyle.Hidden;
                Process.Start(start);
            }
            catch (Exception ex)
            {
                MessageBox.Show("No pude iniciar la terminal: " + ex.Message,
                    "Actinver Terminal", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            for (int attempt = 0; attempt < 60 && !IsHealthy(); attempt++)
                Thread.Sleep(2000);
        }

        if (!IsHealthy())
        {
            MessageBox.Show("La terminal no respondio. Abra iniciar-remoto.bat en el proyecto para ver el motivo, o revise data\\terminal_errores.log.",
                "Actinver Terminal", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        try
        {
            Process.Start(new ProcessStartInfo(LocalUrl) { UseShellExecute = true });
        }
        catch (Exception ex)
        {
            MessageBox.Show("La terminal esta encendida, pero no pude abrir el navegador: " + ex.Message + "\n" + LocalUrl,
                "Actinver Terminal", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }

    private static bool IsHealthy()
    {
        try
        {
            var request = (HttpWebRequest)WebRequest.Create(HealthUrl);
            request.Timeout = 2000;
            request.ReadWriteTimeout = 2000;
            request.Proxy = null;
            using (var response = (HttpWebResponse)request.GetResponse())
                return response.StatusCode == HttpStatusCode.OK;
        }
        catch (WebException)
        {
            return false;
        }
    }
}