use MediaWiki;
use DBI;

$dbh = DBI->connect("dbi:SQLite:dbname=mayors-money","","");

$c = MediaWiki->new;
$c->setup({
    'bot' => {
    'user' => 'accountabot',
    'pass' => 'PASSWORD'},
    'wiki' => {
    'host' => 'stimuluswatch.org',
    'path' => 'mediawiki'
    }}) or die 'Error connecting to wiki';

$sth = $dbh->prepare("select c.name, c.state, p.project_id, p.money, p.num_jobs from projects p join cities c on p.city_id = c.city_id where p.project_id >= 9689 order by p.project_id");
$sth->execute();

while (($name,$state,$project_id, $cost, $jobs) = $sth->fetchrow_array()) {
    $page_name = "$state:$name:$project_id";

    $page_content = "== General Description == \n{{project-stub}}\n\n== Points in Favor ==\n\n== Points Against ==\n";
    print "$page_name ";
    print "\n";

     do {
         $rv = $c->text($page_name, $page_content);
         if ($rv != 1) {
             print "$rv\n";
         print "error: $c->{error}\n";
         }
     } while ($rv != 1);

}

$sth->finish();
$dbh->disconnect();
